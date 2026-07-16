export interface BadgeProps{
  variant?:'brand'|'accent'|'neutral';
  children:React.ReactNode;
}
export function Badge(props:BadgeProps):JSX.Element;
