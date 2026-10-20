import { readFileSync } from "node:fs";

const config = JSON.parse(readFileSync(new URL("./allurerc.json", import.meta.url), "utf8"));

export default {
  ...config,
  output: "reports/allure-live",
  appendHistory: false,
};
