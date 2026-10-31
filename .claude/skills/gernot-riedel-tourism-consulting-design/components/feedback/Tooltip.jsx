import React from 'react';
export function Tooltip({label,children}){
  return <span className="gr-tooltip-wrap">{children}<span className="gr-tooltip">{label}</span></span>;
}
