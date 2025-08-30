import React from "react";

type Props = {
  fallback: React.ReactNode;
  children: React.ReactNode;
};

type State = { hasError: boolean };

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: any, info: any) {
    // Error logged to browser dev tools for debugging
    if (process.env.NODE_ENV === 'development') {
      console.error("ErrorBoundary caught an error", error, info);
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}
