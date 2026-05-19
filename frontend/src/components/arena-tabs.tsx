import { PageTabs } from "@/components/page-tabs";

export type ArenaTab = "champions" | "hex" | "events" | "items";

export function ArenaTabs({ active }: { active: ArenaTab }) {
  return (
    <PageTabs
      items={[
        { href: "/arena/champions", label: "英雄", active: active === "champions" },
        { href: "/arena", label: "海克斯 Augment", active: active === "hex" },
        { href: "/arena/events", label: "事件選擇", active: active === "events" },
        { href: "/arena/items", label: "裝備", active: active === "items" },
      ]}
    />
  );
}
