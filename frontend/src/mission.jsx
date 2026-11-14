// mission.jsx — one shared /mission fetch for the whole app (Topbar, Today, ...).
// Refreshes on an interval so advancing /demo/clock during the demo shows up without a reload.
import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from './api/client.js'

const REFRESH_MS = 15000
const MissionContext = createContext({ mission: null, refresh: () => {} })

export function MissionProvider({ children }) {
  const [mission, setMission] = useState(null)

  const refresh = useCallback(() => {
    api.getMission().then(setMission).catch(() => {}) // keep the last good value if one fetch fails
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, REFRESH_MS)
    return () => clearInterval(id)
  }, [refresh])

  return <MissionContext.Provider value={{ mission, refresh }}>{children}</MissionContext.Provider>
}

// { mission, refresh } — call refresh() right after POST /demo/clock
export function useMission() {
  return useContext(MissionContext)
}
