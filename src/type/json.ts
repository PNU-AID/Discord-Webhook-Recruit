export interface HomepageList {
  data: HomepageItem[];
  latestPostIndex: number;
}

export interface HomepageItem {
  url: string;
  name: string;
}

export interface KeywordList {
  aiKeywords: string[];
}
