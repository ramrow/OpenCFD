# chainlit_ui.py
import os
import json
from typing import Dict, Any

import httpx
import chainlit as cl

BACKEND_URL = "http://localhost:7860/run_foambench"


async def call_backend(user_requirement: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(
                BACKEND_URL,
                json={"user_requirement": user_requirement},
            )
            # Let caller handle status codes
            try:
                return resp.json()
            except:
                return {
                    "error": "Backend returned invalid JSON",
                    "raw": resp.text,
                    "status": resp.status_code
                }
    except httpx.HTTPStatusError as e:
        try:
            err = e.response.json()
        except:
            err = e.response.text
        return {"error": f"HTTP {e.response.status_code}", "details": err}
    except Exception as e:
        return {"error": "Request failed", "details": repr(e)}


def format_file_tree(files_dict: Dict[str, Any], prefix: str = "") -> str:
    lines = []
    for name, content in sorted(files_dict.items()):
        path = f"{prefix}/{name}" if prefix else name
        if isinstance(content, dict):
            lines.append(f"{prefix}folder {name}/")
            lines.extend(format_file_tree(content, prefix + "    ").splitlines())
        else:
            lines.append(f"{prefix}file {name}")
            if isinstance(content, str) and content.strip():
                preview = content.strip().splitlines()[0]
                if len(preview) > 80:
                    preview = preview[:77] + "..."
                lines.append(f"{prefix}    {preview}")
    return "\n".join(lines)


@cl.on_chat_start
async def on_chat_start():
    await cl.Message(
        content=(
            "I am OpenCFD, your assistant helper for automating openfoam simulations. Please send me your user requirement."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    user_text = message.content.strip()
    if not user_text:
        await cl.Message(content="Please enter a requirement.").send()
        return

    running_msg = cl.Message(content="Running Foam-Agent...")
    await running_msg.send()

    result = await call_backend(user_text)

    # Handle backend errors
    if "error" in result:
        pretty = json.dumps(result, indent=2, ensure_ascii=False)
        content = f"**Backend Error**\n\n```json\n{pretty}\n```"
        running_msg.content = content
        await running_msg.update()
        return

    # Extract data
    returncode = result.get("returncode", "N/A")
    stdout = (result.get("stdout") or "").strip()
    stderr = (result.get("stderr") or "").strip()
    files_tree = result.get("files", {})

    # Build file tree display
    if "_error" in files_tree:
        tree_block = f"**Warning**: {files_tree['_error']}"
    else:
        tree_text = format_file_tree(files_tree)
        tree_block = f"```text\n{tree_text}\n```"

    # Header
    header = (
        f"**Foam-Agent Finished**\n\n"
        f"- **Return code:** `{returncode}`\n"
        f"- **Output dir:** `{result.get('output_dir')}`\n\n"
        f"**Generated Files:**\n{tree_block}"
    )

    # Optional: stdout/stderr in collapsible
    details = []
    if stdout:
        details.append(
            "<details><summary>STDOUT</summary>\n\n"
            f"```text\n{stdout[:3000]}\n```\n</details>"
        )
    if stderr:
        details.append(
            "<details><summary>STDERR</summary>\n\n"
            f"```text\n{stderr[:3000]}\n```\n</details>"
        )

    content = header
    if details:
        content += "\n\n" + "\n\n".join(details)

    running_msg.content = content
    await running_msg.update()