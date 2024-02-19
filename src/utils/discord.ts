import axios from "axios";
import { ContentType } from "../type/content";

export function convertDataWithTemplate(data: ContentType[]) {
  let content = "[오늘의 채용 공고]\n\n";
  for (const item of data) {
    content += `공고: ${item.contentLabel}\n링크: <${item.contentUrl}>\n\n`;
  }
  content += "";
  return content;
}

export async function sendDiscordNotification(message: string) {
  try {
    const WEBHOOK_URL = process.env.AID_DISCORD_WEBHOOK_URL;
    if (!WEBHOOK_URL) {
      throw new Error("webhook url is nothing!!");
    }
    const res = await axios.post(WEBHOOK_URL, {
      content: message,
      embed: [
        {
          title: "오늘의 채용 공고",
          description: message,
          color: 0x00ff00,
          timestamp: new Date(),
          fields: [
            {
              name: "필드 1 제목",
              value: "필드 1 내용",
              inline: false,
            },
            {
              name: "필드 12 제목",
              value: "필드 12 내용",
              inline: false,
            },
          ],
          footer: {
            text: "KimCookieYa",
          },
        },
      ],
    });
    // console.log("result:", res);
    return true;
  } catch (error) {
    console.error(error);
    return false;
  }
}
