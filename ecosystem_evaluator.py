import os
import json
import streamlit as st
from openai import OpenAI

# UI setup
st.set_page_config(page_title="Ecosystem Evaluator", page_icon="🌐", layout="centered")
st.title("🌐 Ecosystem Evaluator")
st.write("Paste your ecosystem analysis below. The agent will evaluate it against Ron Adner's ecosystem framework and return a compact assessment.")

# Sidebar: API key and model
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
model = st.sidebar.text_input("Model", value="gpt-5-nano")

# Text input
user_text = st.text_area("Submission Text", height=400, placeholder="Paste your ecosystem analysis here (complementors/intermediaries, MVE, and risks)...")

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
                "Evaluate user-submitted documents that apply Ron Adner's ecosystem framework to a digital business model, following a structured, rubric-based assessment.\n\n"
                "# Instructions\n"
                "- Expect user submissions to include three required parts:\n"
                "   1. A description of the core complementors and intermediaries in the ecosystem.\n"
                "   2. A definition of the minimal viable ecosystem (MVE) for the digital business model.\n"
                "   3. An analysis of the core ecosystem risks.\n"
                "- Evaluate each part according to these criteria:\n"
                "   1. **Part 1: Core complementors and intermediaries**\n"
                "      - Does the submission identify the key complementors and intermediaries relevant to the business model?\n"
                "   2. **Part 2: Minimal viable ecosystem**\n"
                "      - Is the minimal viable ecosystem clearly defined, outlining the essential partners required for successful value proposition delivery?\n"
                "   3. **Part 3: Core ecosystem risks**\n"
                "      - Are the major ecosystem risks identified, such as adoption chain risk, co-innovation risk, or execution risk?\n"
                "- For each criterion, indicate a result: \"yes\" or \"no\", with a concise justification of 1-2 sentences.\n"
                "- If a required section or aspect is missing, mark it as \"no\" and state the omission in the justification.\n"
                "- Assign a final grade: \"pass\" only if every aspect receives \"yes\"; otherwise, assign \"fail\".\n"
                "- Provide an \"overall_comments\" field summarizing general feedback, or an empty string if not applicable.\n\n"
                "# Output Format\n"
                "Respond in the following JSON structure:\n"
                "{\n"
                "  \"part1_complementors_intermediaries\": {\n"
                "    \"Are key complementors and intermediaries identified?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"part2_mve\": {\n"
                "    \"Is the minimal viable ecosystem defined?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"part3_risks\": {\n"
                "    \"Are core ecosystem risks identified?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"final_grade\": \"pass\"|\"fail\",\n"
                "  \"overall_comments\": \"...\"\n"
                "}\n\n"
                "# Output Verbosity\n"
                "- Each justification must be 1-2 sentences.\n"
                "- Ensure the JSON remains concise while fully addressing the evaluation criteria.\n"
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

                    # Part 1: Complementors and Intermediaries
                    if isinstance(data.get("part1_complementors_intermediaries"), dict):
                        section("Part 1 — Core Complementors and Intermediaries")
                        render_items(data["part1_complementors_intermediaries"])

                    # Part 2: Minimal Viable Ecosystem
                    if isinstance(data.get("part2_mve"), dict):
                        section("Part 2 — Minimal Viable Ecosystem (MVE)")
                        render_items(data["part2_mve"])

                    # Part 3: Ecosystem Risks
                    if isinstance(data.get("part3_risks"), dict):
                        section("Part 3 — Core Ecosystem Risks")
                        render_items(data["part3_risks"])

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
