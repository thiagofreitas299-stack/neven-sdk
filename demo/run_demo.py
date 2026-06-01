#!/usr/bin/env python3
"""
NEVEN TECH — Demo Script
=========================

This demo shows the full NEVEN platform in action:
1. Starts the API server
2. Connects a perception pipeline (synthetic or webcam)
3. Generates real-time analytics (foot traffic, heatmaps, dwell time)
4. Serves a live dashboard

Usage:
    python demo/run_demo.py                    # Synthetic data (no camera needed)
    python demo/run_demo.py --source 0         # Use webcam
    python demo/run_demo.py --source rtsp://.. # Use RTSP stream
    python demo/run_demo.py --model yolov8n    # Use YOLO detection

Open http://localhost:8420 to see the dashboard.
"""

import sys
import os
import time
import threading
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neven.utils.logging import setup_logging
from neven.core.config import NevenConfig
from neven.api.server import create_app


def main():
    parser = argparse.ArgumentParser(description="NEVEN Demo")
    parser.add_argument("--source", default="synthetic", help="Video source")
    parser.add_argument("--model", default="builtin", help="Detection model")
    parser.add_argument("--port", type=int, default=8420, help="Server port")
    parser.add_argument("--no-perception", action="store_true", help="Skip auto-starting perception")
    args = parser.parse_args()

    setup_logging(level="INFO", show_banner=True)

    print("  NEVEN DEMO MODE")
    print("  " + "=" * 50)
    print(f"  Source:     {args.source}")
    print(f"  Model:      {args.model}")
    print(f"  Port:       {args.port}")
    print(f"  Dashboard:  http://localhost:{args.port}")
    print(f"  API Docs:   http://localhost:{args.port}/docs")
    print("  " + "=" * 50)
    print()

    # Configure
    config = NevenConfig.from_env()
    config.port = args.port
    config.detection_model = args.model

    # Create app
    app = create_app(config)

    # Auto-start perception after server starts
    if not args.no_perception:
        @app.on_event("startup")
        async def _auto_start():
            import asyncio
            await asyncio.sleep(2)
            # Start perception via internal API
            import httpx
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"http://localhost:{args.port}/v1/perception/start",
                        params={"source": args.source, "model": args.model},
                    )
                    if resp.status_code == 200:
                        print(f"\n  [OK] Perception pipeline auto-started ({args.source})")
                    else:
                        print(f"\n  [WARN] Perception start returned: {resp.status_code}")
            except Exception as e:
                # Fallback: start directly
                from neven.perception.pipeline import PerceptionPipeline
                try:
                    src = int(args.source) if args.source.isdigit() else args.source
                except:
                    src = args.source
                pipeline = PerceptionPipeline(source=src, model_name=args.model)
                pipeline.start()
                app.state.perception_pipeline = pipeline
                print(f"\n  [OK] Perception pipeline started directly ({args.source})")

    # Run server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
