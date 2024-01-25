export interface HomepageList {
  data: HomepageItem[];
  latestPostIndex: number;
}

export interface HomepageItem {
  url: string;
  name: string;
}
