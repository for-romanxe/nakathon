// Cite.jsx — a source id ("hrp:sm-03#p5") that opens that paragraph on the Procedures screen.
import { Link } from 'react-router-dom'

export default function Cite({ id }) {
  return <Link className="cite" to={`/procedures?id=${encodeURIComponent(id)}`}>{id}</Link>
}
