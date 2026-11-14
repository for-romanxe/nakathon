// bodyRegions.js — body regions for the hologram and the Body screen.
// metrics: the band readings the region shows. sensor: 'band' (measured there), 'whole' (a whole-body reading
// shown for reference, e.g. activity for each leg) or 'none' (nothing measures this part).
// location: the body_location value proposed for contracts/enums.json (team, 11/14), used to place symptom reports.
// doc: on-device source for the region note (null when the mockup's source is not in the documents).
export const REGIONS = [
  { id: 'head', location: 'head', metrics: ['sleep'], sensor: 'band', doc: 'hrp:sleep-02#p1' },
  { id: 'heart', location: 'chest', metrics: ['hr', 'hrv'], sensor: 'band', doc: 'hrp:sm-03#p2' },
  { id: 'core', location: 'abdomen', metrics: ['temp'], sensor: 'band', doc: 'hrp:sm-01#p1' },
  { id: 'left_arm', location: 'left_arm', metrics: ['eda'], sensor: 'band', doc: null }, // the band is on this wrist
  { id: 'right_arm', location: 'right_arm', metrics: [], sensor: 'none', doc: null },
  { id: 'left_leg', location: 'left_leg', metrics: ['act'], sensor: 'whole', doc: 'hrp:sm-03#p5' },
  { id: 'right_leg', location: 'right_leg', metrics: ['act'], sensor: 'whole', doc: 'hrp:sm-03#p5' },
]

export const REGION_BY_LOCATION = Object.fromEntries(REGIONS.map((r) => [r.location, r.id]))
