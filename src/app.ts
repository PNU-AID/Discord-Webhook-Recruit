import dotenv from "dotenv";

import { job } from "./utils/job";
import axios from "axios";

dotenv.config();
axios.defaults.headers.common["Accept-Encoding"] = "gzip";

async function main() {
  // 매일 대한민국 오후 8시에 실행
  console.log("크롤링 작업을 시작합니다.");
  await job();
  console.log("크롤링 작업이 종료되었습니다.");
}

(async () => {
  await main();
  process.exit(0);
})();
