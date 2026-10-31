export interface TabsProps{
  tabs:string[];
  active?:string;
  onChange?:(tab:string)=>void;
}
export function Tabs(props:TabsProps):JSX.Element;
