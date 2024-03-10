export const Catogory = {
  AI_NEWBIE: "AI 신입",
  AI_EXPERT: "AI 경력",
  DATA_NEWBIE: "Data 신입",
  DATA_EXPERT: "Data 경력",
  NOTAI: "AI 아닌 것",
};

export type Category = keyof typeof Catogory;
