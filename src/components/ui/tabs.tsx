import { createContext, useContext, useState, type HTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/cn";

type TabsState = { value: string; setValue: (value: string) => void };

const TabsContext = createContext<TabsState | null>(null);

function useTabs() {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error("Tabs parts must be used inside <Tabs>");
  return ctx;
}

export function Tabs({ defaultValue, children }: { defaultValue: string; children: ReactNode }) {
  const [value, setValue] = useState(defaultValue);
  return <TabsContext.Provider value={{ value, setValue }}>{children}</TabsContext.Provider>;
}

export function TabsList({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div role="tablist" className={cn("flex-wrap", className)} {...props} />;
}

export function TabsTrigger({ value, className, children }: { value: string; className?: string; children: ReactNode }) {
  const tabs = useTabs();
  const active = tabs.value === value;
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={() => tabs.setValue(value)}
      className={cn(
        "inline-flex items-center gap-2 rounded-lg px-4 py-2 font-medium transition-colors",
        active
          ? "bg-white text-gray-900 shadow dark:bg-gray-900 dark:text-white"
          : "text-gray-700 hover:bg-white/60 dark:text-gray-300 dark:hover:bg-gray-700",
        className
      )}
    >
      {children}
    </button>
  );
}

export function TabsContent({ value, className, children }: { value: string; className?: string; children: ReactNode }) {
  const tabs = useTabs();
  // Only the open tab is rendered, so hidden tabs cost nothing.
  if (tabs.value !== value) return null;
  return (
    <div role="tabpanel" className={cn("mt-6", className)}>
      {children}
    </div>
  );
}
