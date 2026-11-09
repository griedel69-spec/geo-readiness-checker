import React from 'react';
export function Badge({variant='brand',children}){
  return <span className={`gr-badge gr-badge-${variant}`}>{children}</span>;
}
