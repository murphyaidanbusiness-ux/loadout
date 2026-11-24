"use client";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export default function Dashboard() {
  const [slots, setSlots] = useState<any[]>([]);
  useEffect(() => {
    supabase.from("slots").select("*").then(({ data }) => setSlots(data ?? []));
  }, []);
  return (
    <main>
      <h1>Your walks</h1>
      <ul>{slots.map((s) => <li key={s.id}>{s.starts_at} with {s.walker_name}</li>)}</ul>
    </main>
  );
}
