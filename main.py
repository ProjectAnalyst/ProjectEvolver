"""
Main entry point for Project Evolver.

This script provides the command-line interface for running the project evolution process.
"""

import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv
from src.core.orchestrator import ProjectEvolver


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('project_evolver.log'),
            logging.StreamHandler()
        ]
    )


def main():
    """Main entry point for the application."""
    # Load environment variables first
    load_dotenv()
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Project Evolver - Automatically evolve codebases based on whitepaper specifications')
    parser.add_argument('repository', help='GitHub repository in username/repo format')
    parser.add_argument('--config', help='Path to configuration file', default='config.json')
    parser.add_argument('--whitepaper', help='Path to whitepaper file (optional, will look in docs/whitepaper.md by default)')
    parser.add_argument('--token', help='GitHub token for authentication')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize project evolver
        evolver = ProjectEvolver(args.config)
        
        # Update GitHub token if provided
        if args.token:
            evolver.config.github_token = args.token
        
        # Start evolution process
        logger.info(f"Starting evolution process for repository: {args.repository}")
        evolver.evolve_project(args.repository, args.whitepaper)
        
        logger.info("Project evolution completed successfully")
        
    except Exception as e:
        logger.error(f"Project evolution failed: {str(e)}")
        raise


if __name__ == '__main__':
    main() 