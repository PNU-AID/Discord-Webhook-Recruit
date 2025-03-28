import fs from "fs";
import { HomepageList, KeywordList } from "../type/json";

export function extractPostIdInId(contentId: string): number {
  const splitedContentId = contentId.split("/").at(-1);
  if (splitedContentId) {
    return Number(splitedContentId);
  }
  return -1;
}

const HOMEPAGE_JSON = "data/homepage.json";

export function getHomepageList() {
  const homepageListFile = fs.readFileSync(HOMEPAGE_JSON, "utf-8");
  const homepageList = JSON.parse(homepageListFile) as HomepageList;
  // 다음 알림 전송때 중복으로 전송하지 않기 위해 latestPostIndex 기록
  const latestPostIndex = homepageList.latestPostIndex;
  return {
    homepageList,
    latestPostIndex,
  };
}

export function updateLatestPostIndex(id: number) {
  try {
    const homepageFile = fs.readFileSync(HOMEPAGE_JSON, "utf-8");
    const homepageList = JSON.parse(homepageFile) as HomepageList;
    homepageList.latestPostIndex = id;
    const updatedHomepageListContent = JSON.stringify(homepageList, null, 2);
    fs.writeFileSync(HOMEPAGE_JSON, updatedHomepageListContent, "utf-8");
    return true;
  } catch (error) {
    console.error(error);
    return false;
  }
}

export function isRelatedToAi(text: string) {
  const keywordFile = fs.readFileSync("data/keyword.json", "utf-8");
  const keywordList = JSON.parse(keywordFile) as KeywordList;
  const lowerText = text.toLowerCase();

  return keywordList.aiKeywords.some(
    (keyword) =>
      lowerText.includes(keyword) &&
      !lowerText.includes("research") &&
      !lowerText.includes("리서치")
  );
}

export function removeExtraSpaces(sentence: string): string {
  return sentence.replace(/\s+/g, " ");
}

export function isNotRelatedToAi(text: string) {
  return (
    text.includes("프론트") ||
    text.includes("백엔드") ||
    text.includes("Front") ||
    text.includes("Back")
  );
}
