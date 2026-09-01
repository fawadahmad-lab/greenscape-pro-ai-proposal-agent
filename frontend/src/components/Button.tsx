import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode, MouseEventHandler } from "react";
import { Link } from "react-router-dom";

type Variant = "primary" | "secondary" | "success" | "danger" | "ghost" | "ghostLight";
type Size = "sm" | "md" | "lg";

interface CommonProps {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  disabled?: boolean;
  icon?: ReactNode;
  children?: ReactNode;
  className?: string;
}

interface ButtonAsButton extends CommonProps, ButtonHTMLAttributes<HTMLButtonElement> {
  as?: "button";
  to?: undefined;
  onClick?: MouseEventHandler<HTMLButtonElement>;
}

interface ButtonAsLink extends CommonProps {
  as: "link";
  to: string;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
}

export type ButtonProps = ButtonAsButton | ButtonAsLink;

function classNames(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export default forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  props,
  ref
) {
  const {
    variant = "primary",
    size = "md",
    loading = false,
    disabled,
    icon,
    children,
    className,
  } = props;

  const variantClass: Record<Variant, string> = {
    primary: "btn-primary",
    secondary: "btn-secondary",
    success: "btn-success",
    danger: "btn-danger",
    ghost: "btn-ghost",
    ghostLight: "btn-ghost-light",
  };
  const sizeClass = size === "sm" ? "btn-sm" : size === "lg" ? "btn-lg" : "";

  const classes = classNames(
    "btn",
    variantClass[variant],
    sizeClass,
    icon && !children ? "btn-icon" : "",
    loading ? "is-loading" : "",
    className
  );

  const content = (
    <>
      {loading ? (
        <span className="btn-spinner" aria-hidden="true" />
      ) : (
        icon && <span aria-hidden="true">{icon}</span>
      )}
      {children !== undefined && children}
    </>
  );

  if (props.as === "link") {
    return (
      <Link to={props.to} className={classes} onClick={props.onClick}>
        {content}
      </Link>
    );
  }

  const isDisabled = loading || disabled;
  const { type, title, "aria-label": ariaLabel, onClick } =
    props as ButtonAsButton;

  return (
    <button
      ref={ref}
      type={type ?? "button"}
      className={classes}
      onClick={(e) => {
        if (isDisabled) return;
        onClick?.(e);
      }}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      title={title}
      aria-label={ariaLabel}
    >
      {content}
    </button>
  );
});
