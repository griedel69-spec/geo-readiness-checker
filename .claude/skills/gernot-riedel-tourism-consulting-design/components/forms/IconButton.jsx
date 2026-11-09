import React from 'react';
export function IconButton({children,onClick,disabled=false,label}){
  return <button type="button" aria-label={label} disabled={disabled} onClick={onClick} className="gr-iconbtn">{children}</button>;
}
