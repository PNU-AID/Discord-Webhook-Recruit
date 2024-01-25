import axios from "axios";
import * as cheerio from "cheerio";
import fs from "fs";
import { HomepageList } from "./type/json";
import { ContentType } from "./type/content";

export async function crawlWebsite() {
  const homepageListFile = fs.readFileSync("data/homepage.json", "utf-8");
  const homepageList = JSON.parse(homepageListFile) as HomepageList;
  const latestPostIndex = homepageList.latestPostIndex;
  // console.log(homepageList);

  const linkData: ContentType[] = [];

  for (const homepageItem of homepageList.data) {
    const response = await axios.get(homepageItem.url);
    const $ = cheerio.load(response.data);
    const links = $(".post-content article").find("a");

    links.each(function () {
      const contentUrl = $(this).attr("href");
      const contentLabel = $(this).attr("aria-label");
      linkData.push({
        contentUrl: contentUrl || "https://www.naver.com/",
        contentLabel: contentLabel || "네이버(기본값)",
      });
    });

    console.log(linkData.slice(0, 10));
  }
}
