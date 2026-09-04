export default function ViewfinderMark({ size = 40, animate = true, className = "" }) {
  // Corner brackets that sit at a landscape rect by default, and animate to a
  // portrait rect on a slow loop -- this is the whole product in one shape.
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <g stroke="#ffb238" strokeWidth="3" strokeLinecap="square">
        {/* top-left */}
        <path d="M 10 22 L 10 14 L 18 14">
          {animate && (
            <animate
              attributeName="d"
              values="M 10 22 L 10 14 L 18 14; M 18 10 L 10 10 L 10 18; M 10 22 L 10 14 L 18 14"
              dur="4s"
              repeatCount="indefinite"
              keyTimes="0;0.5;1"
            />
          )}
        </path>
        {/* top-right */}
        <path d="M 54 22 L 54 14 L 46 14">
          {animate && (
            <animate
              attributeName="d"
              values="M 54 22 L 54 14 L 46 14; M 46 10 L 54 10 L 54 18; M 54 22 L 54 14 L 46 14"
              dur="4s"
              repeatCount="indefinite"
              keyTimes="0;0.5;1"
            />
          )}
        </path>
        {/* bottom-left */}
        <path d="M 10 42 L 10 50 L 18 50">
          {animate && (
            <animate
              attributeName="d"
              values="M 10 42 L 10 50 L 18 50; M 18 54 L 10 54 L 10 46; M 10 42 L 10 50 L 18 50"
              dur="4s"
              repeatCount="indefinite"
              keyTimes="0;0.5;1"
            />
          )}
        </path>
        {/* bottom-right */}
        <path d="M 54 42 L 54 50 L 46 50">
          {animate && (
            <animate
              attributeName="d"
              values="M 54 42 L 54 50 L 46 50; M 46 54 L 54 54 L 54 46; M 54 42 L 54 50 L 46 50"
              dur="4s"
              repeatCount="indefinite"
              keyTimes="0;0.5;1"
            />
          )}
        </path>
      </g>
      <circle cx="32" cy="32" r="3" fill="#ffb238" />
    </svg>
  );
}
