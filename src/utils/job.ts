import axios from "axios";
import * as cheerio from "cheerio";

import { HomepageList } from "../type/json";
import { ContentType } from "../type/content";
import {
  extractPostIdInId,
  getHomepageList,
  updateLatestPostIndex,
} from "./util";
import { convertDataWithTemplate, sendDiscordNotification } from "./discord";

export async function crawlWebsite() {
  // 크롤링할 대상 사이트 리스트를 가져온다.
  const { homepageList, latestPostIndex } = getHomepageList();
  // console.log(homepageList);

  const linkData: ContentType[] = [];

  // 사이트별로 크롤링 수행 후, 필요한 데이터만을 추출한다.
  for (const homepageItem of homepageList.data) {
    let newLatestPostIndex = latestPostIndex;
    try {
      console.log(homepageItem.url, "작업 중...");
      const response = await axios.get(homepageItem.url);
      const $ = cheerio.load(response.data);
      const links = $(".fusion-image-wrapper").find("a");

      links.each(function () {
        const contentUrl = $(this).attr("href");
        const contentLabel = $(this).attr("aria-label");

        const id = contentUrl?.split("/").at(-1);
        if (!id) {
          return;
        }
        const contentId = extractPostIdInId(id);
        console.log(contentId);
        if (contentId <= latestPostIndex) {
          return;
        } else if (contentId > latestPostIndex) {
          newLatestPostIndex = contentId;
        }

        linkData.push({
          contentUrl: contentUrl || "https://www.naver.com/",
          contentLabel: contentLabel || "네이버(기본값)",
        });
      });

      console.log(linkData.slice(0, 10));
    } catch (error) {
      console.error(
        "다음 페이지를 읽다가 에러가 발생하였습니다.",
        homepageItem.url
      );
    }

    // TODO: 데이터에 템플릿을 적용 이후, 디코에 전송
    if (linkData.length > 0) {
      const contentWithTemplate = convertDataWithTemplate(
        linkData.slice(0, 10)
      );
      await sendDiscordNotification(contentWithTemplate);
      updateLatestPostIndex(newLatestPostIndex);
    }
  }
}
