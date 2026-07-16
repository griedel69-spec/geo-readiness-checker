export interface IconButtonProps{
  children:React.ReactNode;
  onClick?:()=>void;
  disabled?:boolean;
  label:string;
}
export function IconButton(props:IconButtonProps):JSX.Element;
