module.exports = function (api) {
  api.cache(true);
  return {
    presets: ["babel-preset-expo"],
    plugins: [
      [
        "module-resolver",
        {
          root: ["./"],
          alias: {
            "@core": "./src/core",
            "@infra": "./src/infrastructure",
            "@presentation": "./src/presentation",
            "@shared": "./src/shared",
          },
        },
      ],
      [
        "@babel/plugin-transform-inline-environment-variables",
        {
          include: ["API_BASE", "FIREBASE_PROJECT_ID"],
        },
      ],
    ],
  };
};
