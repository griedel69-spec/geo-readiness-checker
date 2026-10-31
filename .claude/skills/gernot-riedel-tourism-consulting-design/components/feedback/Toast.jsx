import React from 'react';
export function Toast({children,accent=false}){
  return <div className={`gr-toast${accent?' gr-toast-accent':''}`}>{children}</div>;
}
