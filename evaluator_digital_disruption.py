import os
import json
import streamlit as st
from openai import OpenAI

# UI setup
st.set_page_config(page_title="Digital Disruption Evaluator", page_icon="🧭", layout="centered")
st.title("🧭 Digital Disruption Evaluator")
st.write("Paste your assignment text below. The agent will evaluate it against the rubric and return a compact assessment.")

# Sidebar: API key and model
st.sidebar.header("Settings")
api_key = st.secrets["OPENAI_API_KEY"]
os.environ["OPENAI_API_KEY"] = api_key
model = st.sidebar.text_input("Model", value="gpt-5-nano")

# Text input
user_text = st.text_area("Submission Text", height=400, placeholder="Paste the full document here (BMC, disruptors, and strategies)...")

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
                "Evaluate user-submitted documents analyzing a company's digital disruption scenario in three structured steps, providing a detailed, rubric-based assessment.\n\n"
                "# Instructions\n"
                "- Expect user submissions to include three main parts:\n"
                "   1. A detailed business model description, structured using the business model canvas methodology.\n"
                "   2. Descriptions of two digital disruptors, including: what they do, why they are disruptive, and their disruption strategies.\n"
                "   3. Strategies for the company to either team up, fight back, or escape, each with explanations and pros/cons.\n"
                "- Evaluate each part according to these criteria:\n"
                "   1. **Part 1:**\n"
                "      - Is the business model description clear and logical?\n"
                "      - Are all components of the business model canvas mentioned?\n"
                "   2. **Part 2:**\n"
                "      - Has the user identified two relevant digital disruptors?\n"
                "      - Are their relevance and disruptive nature clearly explained?\n"
                "   3. **Part 3:**\n"
                "      - Are all three strategies (team up, fight back, escape) discussed?\n"
                "      - Are both advantages and disadvantages presented for each strategy, with logical reasoning?\n"
                "- For each criterion, indicate a result: \"yes\" or \"no\", with a concise (1-2 sentences) justification.\n"
                "- If a required section or aspect is missing, mark it as \"no\" and state the omission in the justification.\n"
                "- Assign a final grade: \"pass\" only if every aspect receives \"yes\"; otherwise, assign \"fail\".\n"
                "- Provide an 'overall_comments' field with summary remarks as needed, or an empty string if not applicable.\n\n"
                "# Output Format\n"
                "Respond in the following JSON format:\n"
                "{\n"
                "  \"part1\": {\n"
                "    \"Clear business canvas model description provided?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"},\n"
                "    \"Are all canvas parts mentioned?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"part2\": {\n"
                "    \"Are two disruptors identified?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"},\n"
                "    \"Is disruptors' relevance explained?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"part3\": {\n"
                "    \"Are all strategies discussed?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"},\n"
                "    \"Are pros and cons provided for each strategy?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"final_grade\": \"pass\"|\"fail\",\n"
                "  \"overall_comments\": \"...\"\n"
                "}\n\n"
                "# Output Verbosity\n"
                "- For each justification, respond with 1–2 sentences only.\n"
                "- Ensure the entire JSON does not include explanations exceeding these targets.\n"
                "- Prioritize complete, actionable answers within these length limits.\n"
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
    elif not api_key and not os.environ.get("OPENAI_API_KEY"):
        st.warning("Provide an OpenAI API key in the sidebar or set OPENAI_API_KEY.")
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

                    # Part 1
                    if isinstance(data.get("part1"), dict):
                        section("Part 1 — Business Model")
                        render_items(data["part1"])

                    # Part 2
                    if isinstance(data.get("part2"), dict):
                        section("Part 2 — Disruptors")
                        render_items(data["part2"])

                    # Part 3
                    if isinstance(data.get("part3"), dict):
                        section("Part 3 — Strategies")
                        render_items(data["part3"])

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
