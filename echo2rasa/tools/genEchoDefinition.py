import argparse
from echomodel import EchoModel


def readArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--invocation",
                        help="Echo skill invocation name", default="rasademo")
    parser.add_argument(
        "-d", "--domain", help="domain definition file", default="..\\..\\domain.yml")
    parser.add_argument(
        "-n", "--nlu", help="nlu training file", default="..\\..\\data\\nlu.md")
    parser.add_argument(
        "-e", "--echoconf", help="echo related configurations",
        default="..\\echo_domain.yml")
    parser.add_argument(
        "-o", "--output", help="output path to echo configuration file",
        default="echoSkillConfiguration.json")
    return parser.parse_args()


if __name__ == "__main__":
    args = readArgs()
    echoModel = EchoModel(args.invocation, args.domain,
                          args.nlu, args.echoconf)
    echoModel.export2echo(args.output)
    # print(echoModel)
    print(f'Alexa/Echo model dumped to {args.output}')
