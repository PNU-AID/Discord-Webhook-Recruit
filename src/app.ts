import Koa from "koa";
import cron from "node-cron";
import dotenv from "dotenv";

import { crawlWebsite } from "./utils/job";

dotenv.config();

const app = new Koa();

app.use(async (ctx) => {
  ctx.body = "Hello World";
});

app.listen(3000, () => {
  console.log("Koa server is running!!");
  crawlWebsite();
});

cron.schedule(
  "0 20 * * *",
  () => {
    // 매일 대한민국 오후 8시에 실행
    console.log("크롤링 작업을 시작합니다.");
    crawlWebsite();
    console.log("크롤링 작업이 종료되었습니다.");
  },
  {
    scheduled: true,
    timezone: "Asia/Seoul",
  }
);
