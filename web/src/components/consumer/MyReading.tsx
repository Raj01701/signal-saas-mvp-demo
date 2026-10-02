"use client";

import { useState } from "react";

import { Dashboard } from "@/components/consumer/Dashboard";
import { Onboarding } from "@/components/consumer/Onboarding";
import { saveProfile, useProfile } from "@/lib/profile";

/** Onboarding until a profile is saved on this device, then the dashboard. */
export function MyReading() {
  const profile = useProfile();
  const [editing, setEditing] = useState(false);
  if (profile === undefined) return null;
  if (profile === null || editing) {
    return (
      <Onboarding
        initial={profile}
        onDone={(next) => {
          saveProfile(next);
          setEditing(false);
        }}
      />
    );
  }
  return <Dashboard profile={profile} onEdit={() => setEditing(true)} onForget={() => saveProfile(null)} />;
}
