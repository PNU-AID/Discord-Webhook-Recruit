import Koa from "koa";
import cron from "node-cron";
import { crawlWebsite } from "./job";

const app = new Koa();

app.use(async (ctx) => {
  ctx.body = "Hello World";
});

app.listen(3000, () => {
  console.log("Koa is running on http://localhost:3000");
  crawlWebsite();
});

cron.schedule("0 0 * * *", () => {
  // 매일 자정에 실행
  console.log("크롤링 작업을 시작합니다.");
  crawlWebsite();
});
