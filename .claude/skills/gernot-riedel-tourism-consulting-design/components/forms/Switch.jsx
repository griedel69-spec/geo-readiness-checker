import React from 'react';
export function Switch({checked,onChange,disabled=false,label}){
  return <label className="gr-switch" aria-label={label}>
    <input type="checkbox" checked={checked} onChange={onChange} disabled={disabled}/>
    <span className="gr-switch-track"></span>
    <span className="gr-switch-thumb"></span>
  </label>;
}
