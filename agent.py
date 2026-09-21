from typing import List, Dict, Any
from google import genai
from google.genai import types

from config import (
    gemini_client,
    GEMINI_MODEL,
    GEMINI_FALLBACK_MODEL,
    SYSTEM_PROMPT,
    MAX_STEPS,
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
)

from tools import (
    search_docs,
    lookup_ingredient,
    get_routine,
    escalate,
    build_tool_schemas,
)

from logger import get_logger
from guardrails import check_input
from memory import load_memory, save_memory
from cost_tracker import CostTracker
from resilience import CircuitBreaker, GracefulDegradation, get_cached_response, set_cached_response

def _build_tool_definitions() -> List[types.FunctionDeclaration]:
    tool_schemas = build_tool_schemas()
    declarations = []
    for tool_schema in tool_schemas:
        func = tool_schema["function"]
        params = func["parameters"]
        declarations.append(
            types.FunctionDeclaration(
                name=func["name"],
                description=func["description"],
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        k: types.Schema(
                            type=types.Type.STRING,
                            description=v.get("description", ""),
                        )
                        for k, v in params["properties"].items()
                    },
                    required=params.get("required", []),
                ),
            )
        )
    return declarations

def _execute_tool(function_name: str, args: Dict[str, Any]) -> str:
    try:
        if function_name == "search_docs":
            return search_docs(args.get("query", ""))
        elif function_name == "lookup_ingredient":
            return lookup_ingredient(args.get("name", ""))
        elif function_name == "get_routine":
            return get_routine(args.get("skin_type", ""))
        elif function_name == "escalate":
            return escalate(args.get("reason", ""))
        else:
            return f"ERROR: Unknown tool '{function_name}'"
    except Exception as e:
        return f"ERROR: {str(e)}"

def _parts_to_text(parts) -> str:
    return "".join(p.text for p in parts if p.text)

def run_agent(
    user_input: str,
    session_id: str = "default",
    cost_tracker: CostTracker = None,
) -> Dict[str, Any]:
    if cost_tracker is None:
        cost_tracker = CostTracker(session_id=session_id)

    check_input(user_input, session_id=session_id)

    logger = get_logger(session_id)
    memory = load_memory()

    semantic_cb = CircuitBreaker(failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD, recovery_timeout=CIRCUIT_BREAKER_RECOVERY_TIMEOUT)
    llm_cb = CircuitBreaker(failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD, recovery_timeout=CIRCUIT_BREAKER_RECOVERY_TIMEOUT)

    tool_defs = _build_tool_definitions()
    tool_objects = [types.Tool(function_declarations=tool_defs)]

    cache_key = f"{session_id}_{abs(hash(user_input))}"
    cached = get_cached_response(cache_key)
    if cached:
        return {
            "final_answer": cached,
            "tools_used": [],
            "steps": 0,
            "escalated": False,
            "cached": True,
        }

    conversation = [
        types.Content(role="user", parts=[types.Part.from_text(text=SYSTEM_PROMPT)]),
        types.Content(role="user", parts=[types.Part.from_text(text=user_input)]),
    ]

    tools_used = []
    final_answer = ""
    step = 0
    model_used = GEMINI_MODEL

    while step < MAX_STEPS:
        step += 1
        try:
            response = llm_cb.call(
                gemini_client.models.generate_content,
                model=model_used,
                contents=conversation,
                config=types.GenerateContentConfig(tools=tool_objects, temperature=0.1, max_output_tokens=800),
            )
        except Exception as e:
            if model_used != GEMINI_FALLBACK_MODEL:
                model_used = GEMINI_FALLBACK_MODEL
                continue
            final_answer = f"ERROR: Failed to call Gemini: {str(e)}"
            break

        if not response.candidates:
            final_answer = "I'm sorry, I couldn't generate a response."
            break

        candidate = response.candidates[0]
        content = candidate.content

        function_calls = []
        text_parts = []

        for part in content.parts:
            if part.function_call:
                function_calls.append(part.function_call)
            if part.text:
                text_parts.append(part.text)

        if text_parts and not function_calls:
            final_answer = _parts_to_text(content.parts)
            break

        if function_calls:
            conversation.append(candidate.content)
            tool_parts = []
            for fc in function_calls:
                args_dict = dict(fc.args) if fc.args else {}
                tool_result = _execute_tool(fc.name, args_dict)
                tools_used.append(fc.name)
                tool_parts.append(
                    types.Part.from_function_response(
                        name=fc.name, response={"result": tool_result}
                    )
                )
            conversation.append(types.Content(role="user", parts=tool_parts))
            continue

    if not final_answer:
        from resilience import GracefulDegradation
        final_answer = "I could not complete the request. Please try again."

    save_memory(memory)
    logger.save()

    input_tokens = len(user_input.split())
    output_tokens = len(final_answer.split())
    cost_tracker.start_call(model_used, input_tokens, "chat")
    cost_tracker.end_call(output_tokens, model_used)

    if final_answer and not final_answer.startswith("ERROR"):
        set_cached_response(cache_key, final_answer)

    return {
        "final_answer": final_answer,
        "tools_used": tools_used,
        "steps": step,
        "escalated": (final_answer.startswith("ERROR") or "escalat" in final_answer.lower()),
        "model_used": model_used,
        "cached": False,
    }
