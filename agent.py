from typing import List, Dict, Any
from google import genai
from google.genai import types

from config import (
    gemini_client,
    GEMINI_MODEL,
    SYSTEM_PROMPT,
    MAX_STEPS,
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
    except ValueError as e:
        return f"ERROR: {str(e)}"
    except Exception as e:
        return f"ERROR: {str(e)}"


def _parts_to_text(parts) -> str:
    return "".join(p.text for p in parts if p.text)


def run_agent(user_input: str, session_id: str = "default") -> Dict[str, Any]:
    check_input(user_input)

    logger = get_logger(session_id)
    memory = load_memory()
    tool_defs = _build_tool_definitions()
    tool_objects = [types.Tool(function_declarations=tool_defs)]

    conversation: List[types.Content] = []
    conversation.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=SYSTEM_PROMPT)],
        )
    )
    conversation.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_input)],
        )
    )

    tools_used: List[str] = []
    step = 0
    final_answer = ""

    logger.log_turn(
        turn=step,
        input=user_input,
        tools_used=[],
        result="",
        final_answer="",
    )

    while step < MAX_STEPS:
        step += 1

        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=conversation,
                config=types.GenerateContentConfig(
                    tools=tool_objects,
                ),
            )
        except Exception as e:
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
            conversation.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=final_answer)],
                )
            )
            logger.log_turn(
                turn=step,
                input=user_input,
                tools_used=tools_used,
                result=final_answer,
                final_answer=final_answer,
            )
            break

        if function_calls:
            for fc in function_calls:
                args_dict = dict(fc.args) if fc.args else {}
                tool_result = _execute_tool(fc.name, args_dict)
                tools_used.append(fc.name)

                if tool_result.startswith("ERROR"):
                    conversation.append(
                        types.Content(
                            role="tool",
                            parts=[types.Part.from_text(text=tool_result)],
                        )
                    )
                    final_answer = tool_result
                    logger.log_turn(
                        turn=step,
                        input=user_input,
                        tools_used=tools_used,
                        result=tool_result,
                        final_answer=final_answer,
                    )
                    break

                conversation.append(
                    types.Content(
                        role="model",
                        parts=[
                            types.Part.from_function_response(
                                name=fc.name,
                                response={"content": tool_result},
                            )
                        ],
                    )
                )

            if final_answer and final_answer.startswith("ERROR"):
                break

        if step == MAX_STEPS:
            esc = escalate("Maximum steps reached in agent loop.")
            final_answer = f"I have reached the maximum number of steps. {esc}"
            conversation.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=final_answer)],
                )
            )
            logger.log_turn(
                turn=step,
                input=user_input,
                tools_used=tools_used,
                result=final_answer,
                final_answer=final_answer,
            )
            break

    memory = save_memory(memory)
    logger.save()

    return {
        "final_answer": final_answer,
        "tools_used": tools_used,
        "steps": step,
        "escalated": final_answer.startswith("ERROR") or "escalat" in final_answer.lower(),
    }


if __name__ == "__main__":
    result = run_agent("What causes acne?")
    print(f"\nAnswer: {result['final_answer']}")
    print(f"Tools used: {result['tools_used']}")
    print(f"Steps: {result['steps']}")