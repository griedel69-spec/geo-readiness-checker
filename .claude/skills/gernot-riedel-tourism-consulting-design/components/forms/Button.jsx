import React from 'react';
export function Button({variant='primary',size='md',disabled=false,children,onClick,type='button'}){
  const sizeClass=size==='sm'?' gr-btn-sm':size==='lg'?' gr-btn-lg':'';
  return <button type={type} disabled={disabled} onClick={onClick} className={`gr-btn gr-btn-${variant}${sizeClass}`}>{children}</button>;
}
