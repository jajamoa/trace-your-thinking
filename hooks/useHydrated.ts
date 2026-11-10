"use client"

import { useSyncExternalStore } from "react"

const subscribe = () => () => {}
const getSnapshot = () => true
const getServerSnapshot = () => false

/** Keep persisted-session UI identical on the server and first client render. */
export default function useHydrated() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
