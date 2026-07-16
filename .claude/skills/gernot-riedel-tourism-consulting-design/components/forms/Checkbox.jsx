import React from 'react';
export function Checkbox({label,checked,onChange,disabled=false}){
  return <label className="gr-check-row">
    <input type="checkbox" className="gr-check" checked={checked} onChange={onChange} disabled={disabled}/>
    {label}
  </label>;
}
