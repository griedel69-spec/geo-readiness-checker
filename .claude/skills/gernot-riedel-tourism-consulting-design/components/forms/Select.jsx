import React from 'react';
export function Select({label,options=[],value,onChange,disabled=false}){
  return <div className="gr-field">
    {label&&<label className="gr-label">{label}</label>}
    <select className="gr-select" value={value} onChange={onChange} disabled={disabled}>
      {options.map(o=><option key={o.value||o} value={o.value||o}>{o.label||o}</option>)}
    </select>
  </div>;
}
