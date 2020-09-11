import argparse
import glob
import pandas as pd


def main():
    parser = argparse.ArgumentParser("Outage merger")
    parser.add_argument("--input_directory")
    parser.add_argument("--output")

    opts = parser.parse_args()

    dfs = []
    for f in glob.glob(f"{opts.input_directory}/*.csv"):
        dfs.append(pd.read_csv(f))

    merged = pd.concat(dfs, sort=False)
    merged.to_csv(opts.output)


if __name__ == "__main__":
    main()