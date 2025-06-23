import React from "react";

export const MicrosoftIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 32 32"
    width="28"
    height="28"
    className={className}
    aria-hidden="true"
    focusable="false"
    style={{ marginRight: 12, transition: "transform 0.2s" }}
  >
    <rect width="13" height="13" x="2" y="2" fill="#F35325" rx="2" />
    <rect width="13" height="13" x="17" y="2" fill="#81BC06" rx="2" />
    <rect width="13" height="13" x="2" y="17" fill="#05A6F0" rx="2" />
    <rect width="13" height="13" x="17" y="17" fill="#FFBA08" rx="2" />
  </svg>
);
