// session.js — who is using the app. Crew ids are c1–c4, CMO is c2 (CONTRACT §2).
export const CREW_IDS = ['c1', 'c2', 'c3', 'c4']
const storedViewer = sessionStorage.getItem('crew-health-viewer')
export const CURRENT_CREW = CREW_IDS.includes(storedViewer) ? storedViewer : 'c1'

export function switchViewer(id) {
  sessionStorage.setItem('crew-health-viewer', id)
  window.location.assign('/today')
}
