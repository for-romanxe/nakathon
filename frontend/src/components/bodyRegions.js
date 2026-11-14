// bodyRegions.js — body regions for the pixel body and the Body screen.
// Circles are in 0–1 figure coordinates (from the team mockup); each region lists the metrics it shows.
// doc: on-device source for the region note (null when the mockup's source is not in the documents).
export const REGIONS = [
  { id: 'head', cx: 0.5, cy: 0.09, r: 0.075, metrics: ['sleep'], doc: 'hrp:sleep-02#p1' },
  { id: 'heart', cx: 0.56, cy: 0.33, r: 0.09, metrics: ['hr', 'hrv'], doc: 'hrp:sm-03#p2' },
  { id: 'core', cx: 0.5, cy: 0.44, r: 0.08, metrics: ['temp'], doc: 'hrp:sm-01#p1' },
  { id: 'wrist', cx: 0.15, cy: 0.535, r: 0.055, metrics: ['eda'], doc: null },
  { id: 'legs', cx: 0.5, cy: 0.78, r: 0.11, metrics: ['act'], doc: 'hrp:sm-03#p5' },
]
