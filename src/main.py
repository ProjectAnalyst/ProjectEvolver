import argparse
from typing import List
from .analysis.gap_analyzer import Gap, GapAnalyzer
from .analysis.codebase_analyzer import CodebaseAnalyzer
from .utils.git_manager import GitManager
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Project Evolver - Automated Code Evolution')
    parser.add_argument(
        '--max-features', 
        type=int, 
        default=1,
        help='Maximum number of features to implement in this run (default: 1)'
    )
    parser.add_argument(
        'repo_path',  # Changed from --repo-path to positional argument
        type=str,
        help='Path or GitHub URL of the repository to evolve (e.g., username/repo or full URL)'
    )
    args = parser.parse_args()

    try:
        # Initialize git operator
        git_operator = GitManager(args.repo_path)
        
        # Clone or update repository if it's a GitHub URL
        if '/' in args.repo_path and not args.repo_path.startswith(('/', './')):
            if not git_operator.clone_repository(args.repo_path):
                print(f"Failed to clone repository: {args.repo_path}")
                return 1
            # Update repo_path to the cloned directory
            repo_name = args.repo_path.split('/')[-1].replace('.git', '')
            args.repo_path = str(git_operator.repo_path / repo_name)

        # Initialize components
        gap_analyzer = GapAnalyzer()
        codebase_analyzer = CodebaseAnalyzer()
        
        # Analyze codebase
        logger.info("Starting analysis phase...")
        current_state = codebase_analyzer.analyze_codebase(args.repo_path)
        logger.info(f"Found {len(current_state)} files in codebase")
        
        # Set the analyzed codebase in gap analyzer
        gap_analyzer.codebase_index = current_state

        # Load whitepaper
        whitepaper_path = Path(args.repo_path) / "docs" / "whitepaper.md"
        if not whitepaper_path.exists():
            print(f"Could not find whitepaper at {whitepaper_path}")
            return 1
            
        # Analyze gaps
        logger.info("Starting planning phase...")
        gaps = gap_analyzer.identify_gaps(whitepaper_path, current_state)
        
        # Sort gaps by priority
        prioritized_gaps = sorted(gaps, key=lambda g: g.priority, reverse=True)
        
        # Take only the specified number of gaps
        gaps_to_implement = prioritized_gaps[:args.max_features]
        
        if not gaps_to_implement:
            print("No gaps to implement!")
            return 0

        print(f"Implementing {len(gaps_to_implement)} feature(s)...")

        # Create a new branch for these changes
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        branch_name = f"feature/auto-update-{timestamp}"
        git_operator.create_branch(branch_name)

        # Implement each gap
        for gap in gaps_to_implement:
            try:
                print(f"Implementing: {gap.section}")
                
                # Generate and apply changes
                file_changes = gap_analyzer.implement_gap(gap, current_state)
                
                # Apply each file change
                for file_path, new_content in file_changes.items():
                    full_path = Path(args.repo_path) / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(full_path, 'w') as f:
                        f.write(new_content)
                
                # Stage and commit changes
                commit_message = f"""
Implement {gap.section}

Description: {gap.description}
Status: {gap.status}
Files modified: {', '.join(gap.affected_files)}

Missing components addressed:
{chr(10).join('- ' + comp for comp in gap.implementation_details['missing_components'])}

Implementation approach:
{gap.implementation_details['suggested_approach']}
"""
                git_operator.stage_changes(gap.affected_files)
                git_operator.commit_changes(commit_message)
                
            except Exception as e:
                print(f"Error implementing {gap.section}: {str(e)}")
                continue

        # Push changes
        if git_operator.push_changes(branch_name):
            print(f"""
Implementation complete!
Branch: {branch_name}
Features implemented: {len(gaps_to_implement)}
Please review the changes and merge the branch if satisfied.
""")
        else:
            print("Warning: Failed to push changes to remote repository")

    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main()) 