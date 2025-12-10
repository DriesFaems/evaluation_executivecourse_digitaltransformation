import os
import json
import streamlit as st
from openai import OpenAI

# UI setup
st.set_page_config(page_title="AI Transformation Plan Evaluator", page_icon="🤖", layout="centered")
st.title("🤖 AI Transformation Plan Evaluator")
st.write("Paste your generative AI transformation trajectory below. The agent will evaluate it against the rubric and return a compact assessment.")

# Sidebar: API key and model
st.sidebar.header("Settings")
# Try to get API key from secrets, fallback to environment variable or user input
api_key = st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
if not api_key:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
else:
    st.sidebar.info("Using API key from secrets")
model = st.sidebar.text_input("Model", value="gpt-5-nano")

# Text input
user_text = st.text_area("Submission Text", height=400, placeholder="Paste your transformation plan here (awareness, vision, use cases, and employee engagement actions)...")

# Evaluate button
run = st.button("Evaluate Submission")

# Helper: build the developer system prompt content per your spec
DEV_PROMPT = {
    "role": "developer",
    "content": [
        {
            "type": "input_text",
            "text": (
                "# Role and Objective\n"
                "Evaluate user-submitted documents that outline a generative AI transformation trajectory for a company, following a structured, rubric-based assessment.\n\n"
                "# Instructions\n"
                "- Expect user submissions to include four required parts:\n"
                "   1. A section that creates awareness for the need for a generative AI transformation trajectory (max 300 words).\n"
                "   2. A digital vision for the generative AI transformation trajectory (max 200 words).\n"
                "   3. Two specific use cases for generative AI (max 300 words).\n"
                "   4. Two specific actions to increase employees' willingness to engage in the AI transformation plan (max 300 words).\n"
                "- Evaluate each part according to these criteria:\n"
                "   1. **Part 1: Awareness**\n"
                "      - Does the submission clearly articulate why the company needs a generative AI transformation trajectory?\n"
                "      - Is the argument logically structured and supported by relevant reasoning?\n"
                "   2. **Part 2: Digital Vision**\n"
                "      - Is there a clear and coherent digital vision for the generative AI transformation?\n"
                "   3. **Part 3: Use Cases**\n"
                "      - Are two concrete and relevant use cases proposed?\n"
                "      - Are the use cases described with enough clarity to understand their value and feasibility?\n"
                "   4. **Part 4: Employee Engagement Actions**\n"
                "      - Are two specific actions proposed to increase employee willingness to engage in the AI transformation?\n"
                "      - Are the actions realistic, actionable, and logically justified?\n"
                "- For each criterion, indicate a result: \"yes\" or \"no\", with a concise justification (1-2 sentences).\n"
                "- If a required section or aspect is missing, mark it as \"no\" and mention the omission in the justification.\n"
                "- Assign a final grade: \"pass\" only if every aspect receives \"yes\"; otherwise, assign \"fail\".\n"
                "- Provide an \"overall_comments\" field summarizing general remarks, or an empty string if not needed.\n\n"
                "# Output Format\n"
                "Respond in the following JSON structure:\n"
                "{\n"
                "  \"part1_awareness\": {\n"
                "    \"Is the need for transformation clearly articulated?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"},\n"
                "    \"Is the reasoning logical and relevant?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"part2_vision\": {\n"
                "    \"Is the digital vision clear?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"part3_use_cases\": {\n"
                "    \"Are two use cases provided?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"},\n"
                "    \"Are the use cases clearly described?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"part4_employee_engagement\": {\n"
                "    \"Are two actions provided?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"},\n"
                "    \"Are the actions realistic and justified?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"final_grade\": \"pass\"|\"fail\",\n"
                "  \"overall_comments\": \"...\"\n"
                "}\n\n"
                "# Output Verbosity\n"
                "- Each justification must be 1-2 sentences.\n"
                "- Keep the entire JSON concise while ensuring complete and actionable evaluation.\n"
            )
        }
    ],
}


def call_agent(api_key: str, model: str, user_text: str):
    client = OpenAI(api_key=api_key) if api_key else OpenAI()

    response = client.responses.create(
        model=model,
        input=[
            DEV_PROMPT,
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": user_text,
                    }
                ],
            },
        ],
    )

    # Try to extract text output; Responses API may return parts
    try:
        # If using Responses API, first item often has output_text
        text_out = None
        for out in getattr(response, "output", []) or []:
            if hasattr(out, "content"):
                for c in out.content:
                    if c.type == "output_text":
                        text_out = c.text
                        break
            if text_out:
                break
        if not text_out and hasattr(response, "output_text"):
            text_out = response.output_text
    except Exception:
        text_out = None

    # Fallback: try common fields
    if not text_out:
        text_out = getattr(response, "output_text", None) or getattr(response, "content", None)

    return text_out if isinstance(text_out, str) else json.dumps(response.__dict__, default=str)


if run:
    if not user_text.strip():
        st.warning("Please paste your submission text before evaluating.")
    elif not api_key:
        st.warning("Provide an OpenAI API key in the sidebar, set OPENAI_API_KEY secret, or set OPENAI_API_KEY environment variable.")
    else:
        with st.spinner("Evaluating..."):
            try:
                result = call_agent(api_key, model, user_text)
                # Try to pretty-print JSON if valid
                pretty = None
                try:
                    pretty = json.dumps(json.loads(result), indent=2)
                except Exception:
                    pretty = None
                st.subheader("Result")
                # Render friendly report if JSON matches expected schema
                try:
                    data = json.loads(result)

                    def section(title):
                        st.markdown(
                            f"""
                            <div style='padding:12px 16px;border:1px solid #ddd;border-radius:10px;background:#fafafa;'>
                                <h4 style='margin:0 0 8px 0'>{title}</h4>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    def render_items(items):
                        for key, val in items.items():
                            ok = str(val.get("value", "no")).lower() == "yes"
                            badge = "✅" if ok else "❌"
                            color = "#0f766e" if ok else "#b91c1c"
                            st.markdown(
                                f"""
                                <div style='padding:10px 12px;border:1px solid #eee;border-radius:8px;margin:8px 0;'>
                                   <div style='font-weight:600'>{badge} {key}</div>
                                   <div style='color:{color};font-size:0.95em;margin-top:4px'>{val.get("explanation", "")}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                    # Part 1: Awareness
                    if isinstance(data.get("part1_awareness"), dict):
                        section("Part 1 — Awareness")
                        render_items(data["part1_awareness"])

                    # Part 2: Vision
                    if isinstance(data.get("part2_vision"), dict):
                        section("Part 2 — Digital Vision")
                        render_items(data["part2_vision"])

                    # Part 3: Use Cases
                    if isinstance(data.get("part3_use_cases"), dict):
                        section("Part 3 — Use Cases")
                        render_items(data["part3_use_cases"])

                    # Part 4: Employee Engagement
                    if isinstance(data.get("part4_employee_engagement"), dict):
                        section("Part 4 — Employee Engagement")
                        render_items(data["part4_employee_engagement"])

                    # Final grade banner
                    final_grade = str(data.get("final_grade", "")).lower()
                    if final_grade == "pass":
                        st.success("Final Grade: PASS")
                    elif final_grade == "fail":
                        st.error("Final Grade: FAIL")
                    else:
                        st.info(f"Final Grade: {data.get('final_grade', '')}")

                    # Overall comments
                    comments = data.get("overall_comments", "")
                    if comments:
                        st.markdown("### Overall Comments")
                        st.write(comments)
                except Exception:
                    # Fallback: concise text block (no raw JSON)
                    st.warning("Could not parse the evaluation into sections. Showing compact text.")
                    st.write(result)
            except Exception as e:
                st.error(f"Evaluation failed: {e}")
                st.exception(e)
