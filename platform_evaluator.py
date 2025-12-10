import os
import json
import streamlit as st
from openai import OpenAI

# UI setup
st.set_page_config(page_title="Platform Evaluator", page_icon="🔄", layout="centered")
st.title("🔄 Platform Evaluator")
st.write("Paste your two-sided platform proposal for OMR below. The agent will evaluate it against the rubric and return a compact assessment.")

# Sidebar: API key and model
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
model = st.sidebar.text_input("Model", value="gpt-5-nano")

# Text input
user_text = st.text_area("Submission Text", height=400, placeholder="Paste your platform proposal here (core interactions/actors, chicken-egg solution, and monetization strategy)...")

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
                "Evaluate user-submitted documents that propose a two sided platform idea for OMR. Assess each required section using a clear, rubric-based approach.\n\n"
                "# Instructions\n"
                "- Expect user submissions to include three required parts:\n"
                "   1. A description of the core interactions on the platform and the key actors involved as producers and consumers (max 200 words).\n"
                "   2. An explanation of how OMR could solve the chicken or egg problem for this platform (max 200 words).\n"
                "   3. A description of how OMR can best monetize this platform (max 200 words).\n"
                "- Evaluate each part according to these criteria:\n"
                "   1. **Part 1: Core interactions and actors**\n"
                "      - Does the submission clearly describe the central interactions taking place on the platform?\n"
                "      - Are the producer and consumer groups accurately identified and logically connected to the proposed interactions?\n"
                "   2. **Part 2: Solving the chicken or egg problem**\n"
                "      - Is there a concrete strategy for overcoming the platform's initial user imbalance?\n"
                "   3. **Part 3: Monetization strategy**\n"
                "      - Is at least one realistic monetization model proposed for the platform?\n"
                "- For each criterion, assign a result: \"yes\" or \"no\", with a concise justification of 1-2 sentences.\n"
                "- Mark missing sections or missing aspects with \"no\" and note the omission in the explanation.\n"
                "- Assign a final grade: \"pass\" only if every criterion receives \"yes\"; otherwise, assign \"fail\".\n"
                "- Include an \"overall_comments\" field summarizing feedback or leave it as an empty string.\n\n"
                "# Output Format\n"
                "Respond in the following JSON structure:\n"
                "{\n"
                "  \"part1_interactions_actors\": {\n"
                "    \"Are the core platform interactions described clearly?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"},\n"
                "    \"Are producer and consumer groups identified and connected logically?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"part2_chicken_egg\": {\n"
                "    \"Is there a concrete strategy to solve the chicken or egg problem?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"part3_monetization\": {\n"
                "    \"Is a realistic monetization model proposed?\": {\"value\": \"yes\"|\"no\", \"explanation\": \"...\"}\n"
                "  },\n"
                "  \"final_grade\": \"pass\"|\"fail\",\n"
                "  \"overall_comments\": \"...\"\n"
                "}\n\n"
                "# Output Verbosity\n"
                "- Keep each justification to 1-2 sentences.\n"
                "- Ensure the JSON remains complete and succinct.\n"
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

                    # Part 1: Interactions and Actors
                    if isinstance(data.get("part1_interactions_actors"), dict):
                        section("Part 1 — Core Interactions and Actors")
                        render_items(data["part1_interactions_actors"])

                    # Part 2: Chicken or Egg Problem
                    if isinstance(data.get("part2_chicken_egg"), dict):
                        section("Part 2 — Solving the Chicken or Egg Problem")
                        render_items(data["part2_chicken_egg"])

                    # Part 3: Monetization
                    if isinstance(data.get("part3_monetization"), dict):
                        section("Part 3 — Monetization Strategy")
                        render_items(data["part3_monetization"])

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
