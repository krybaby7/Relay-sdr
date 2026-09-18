# Third-party integrations and notices

Package metadata and distributed license texts below were inspected from the exact installed versions used for verification on 18 September 2026. The notices are copied unchanged. Packages remain separate dependencies; Relay application adapters/catalog/geometry are project source, not copied commercial product templates.

| Package | Version | Declared license | Included notice |
| --- | --- | --- | --- |
| `@json-render/core` | 0.20.0 | Apache-2.0 | [notice](licenses/json-render-core-LICENSE.txt) |
| `@json-render/react` | 0.20.0 | Apache-2.0 | [notice](licenses/json-render-react-LICENSE.txt) |
| `react` | 19.2.3 | MIT | [notice](licenses/react-LICENSE.txt) |
| `react-dom` | 19.2.3 | MIT | [notice](licenses/react-dom-LICENSE.txt) |
| `react-grid-layout` | 2.2.4 | MIT | [notice](licenses/react-grid-layout-LICENSE.txt) |
| `react-draggable` | 4.7.2 | MIT | [notice](licenses/react-draggable-LICENSE.txt) |
| `react-resizable` | 3.2.0 | MIT | [notice](licenses/react-resizable-LICENSE.txt) |
| `zod` | 4.3.6 | MIT | [notice](licenses/zod-LICENSE.txt) |
| `langgraph` | 1.2.11 | MIT | [notice](licenses/langgraph-LICENSE.txt) |
| `langgraph-checkpoint-sqlite` | 3.1.1 | MIT | [notice](licenses/langgraph_checkpoint_sqlite-LICENSE.txt) |
| `langgraph-checkpoint` | 4.2.0 | MIT | [notice](licenses/langgraph_checkpoint-LICENSE.txt) |

json-render core/react are Apache-2.0, not MIT. Their distributed LICENSE texts are retained; the packages did not include a separate NOTICE file. The installed default prompt instructing sample data is not used by Relay. The fixed local catalog and application prompt replace that behavior.

The remaining build/test/runtime dependency resolutions are recorded in `frontend/package-lock.json` and `requirements-constraints.txt`. Installations retain their package notices; compiled JavaScript retains the bundler's legal comments. The notices here cover the integrated UI/orchestration libraries, not a legal opinion or a claim of an exhaustive license-compliance certification of every transitive package.

AG-UI/CopilotKit, Puck, Tambo, OpenPage, Twenty, A2UI, DeepSeek Harness, Mastra, OpenHands and E2B were inspiration/reference projects only. No source from those projects was copied into the application and they are not runtime dependencies. The project does not claim to redistribute their hosted/commercial AI capabilities.
