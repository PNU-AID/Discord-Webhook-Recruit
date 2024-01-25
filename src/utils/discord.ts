import axios from "axios";
import { ContentType } from "../type/content";

export function convertDataWithTemplate(data: ContentType[]) {
  let content = "크롤링 웹훅 테스트 중..\n[오늘의 채용 공고]\n\n";
  for (const item of data) {
    content += `공고: ${item.contentLabel}\n링크: ${item.contentUrl}\n\n`;
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
    axios.post(WEBHOOK_URL, {
      content: message,
    });
    return true;
  } catch (error) {
    console.error(error);
    return false;
  }
}
