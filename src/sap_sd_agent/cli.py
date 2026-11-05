import asyncio
import json

from sap_sd_agent.agent import ask_agent, commit_draft
from sap_sd_agent.gemini_api import load_gemini_config, make_gemini_client


async def chat():
    config = load_gemini_config()
    gemini_client = make_gemini_client(config)

    print("SAP SD Agent（輸入 exit 結束）")
    while True:
        user_text = input("\n你：").strip()
        if user_text.lower() in {"exit", "quit"}:
            break

        reply = await ask_agent(user_text, config, gemini_client)
        print(f"\nAgent：{reply['text']}")

        for activity in reply["activities"]:
            print(f"  MCP tool: {activity['tool']}")

        if reply["draft"]:
            draft = reply["draft"]
            print("\n建單草稿：")
            print(json.dumps(draft, ensure_ascii=False, indent=2))
            confirmed = input("確認建立到 SAP？輸入 yes：").strip().lower()

            if confirmed == "yes":
                draft_id = draft.get("draft_id") or draft.get("result", {}).get(
                    "draft_id"
                )
                result = await commit_draft(draft_id)
                print("建立結果：")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print("已取消，不會寫入 SAP。")

    gemini_client.close()


if __name__ == "__main__":
    asyncio.run(chat())
