import json
import argparse
from pyvis.network import Network
import matplotlib.pyplot as plt
from matplotlib.colors import to_hex
import networkx as nx

def load_data(filename):
    with open(filename) as f:
        data = json.load(f)
    return data["results"]


def filter_data_by_account_ids_and_regions(data, account_ids, regions):
    filtered_data = [
        d
        for d in data
        if (not account_ids or d["accountId"] in account_ids)
        and (
            not regions
            or d["configuration"]["requesterVpcInfo"]["region"] in regions
            or d["configuration"]["accepterVpcInfo"]["region"] in regions
        )
    ]
    return filtered_data


def extract_vpc_peering_info(data):
    vpc_peering_info = []
    for item in data:
        peering_connection = {
            "connection_id": item["resourceId"],
            "requester_vpc_id": item["configuration"]["requesterVpcInfo"]["vpcId"],
            "accepter_vpc_id": item["configuration"]["accepterVpcInfo"]["vpcId"],
            "requester_account_id": item["configuration"]["requesterVpcInfo"][
                "ownerId"
            ],
            "accepter_account_id": item["configuration"]["accepterVpcInfo"]["ownerId"],
        }
        vpc_peering_info.append(peering_connection)
    return vpc_peering_info


def create_vpc_peering_graph(vpc_peering_info):
    G = nx.DiGraph()

    for peering in vpc_peering_info:
        if peering["requester_vpc_id"] not in G.nodes:
            G.add_node(
                peering["requester_vpc_id"], account_id=peering["requester_account_id"]
            )
        if peering["accepter_vpc_id"] not in G.nodes:
            G.add_node(
                peering["accepter_vpc_id"], account_id=peering["accepter_account_id"]
            )

        G.add_edge(
            peering["requester_vpc_id"],
            peering["accepter_vpc_id"],
            connection_id=peering["connection_id"],
        )

    return G


def visualize_vpc_peering_graph(G):
    net = Network(
        height="1300px",
        width="100%",
        notebook=False,
        select_menu=True,
        filter_menu=True,
    )
    net.from_nx(G)

    account_ids = list(set([data["account_id"] for _, data in G.nodes(data=True)]))
    cmap = plt.get_cmap("tab20")
    colors = [to_hex(cmap(i)) for i in range(len(account_ids))]
    account_id_color_map = dict(zip(account_ids, colors))

    for node in net.nodes:
        vpc_id = node["id"]
        account_id = G.nodes[vpc_id]["account_id"]
        node["title"] = f"VPC ID: {vpc_id} Account ID: {account_id}"
        node["label"] = vpc_id[:8]
        node["color"] = account_id_color_map[account_id]

    for edge in net.edges:
        connection_id = edge["connection_id"]
        edge["title"] = f"Connection ID: {connection_id}"
        edge["label"] = connection_id[:8]
        edge["color"] = "gray"

    net.show_buttons(filter_=["physics"])
    net.show("vpc_peering_visualization.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Visualize AWS VPC peering connections."
    )
    parser.add_argument(
        "--accounts",
        metavar="account_id",
        type=str,
        nargs="+",
        help="filter VPCs included in the graph by specific account IDs (comma-separated, no spaces)",
    )
    parser.add_argument(
        "--regions",
        metavar="region",
        type=str,
        nargs="+",
        help="filter VPCs included in the graph by specific regions (comma-separated, no spaces)",
    )
    args = parser.parse_args()

    if args.accounts:
        account_ids = args.accounts[0].split(",")
    else:
        account_ids = None

    if args.regions:
        regions = args.regions[0].split(",")
    else:
        regions = None

    data = load_data("vpc_peering_data.json")

    filtered_data = filter_data_by_account_ids_and_regions(data, account_ids, regions)

    vpc_peering_info = extract_vpc_peering_info(filtered_data)
    G = create_vpc_peering_graph(vpc_peering_info)
    visualize_vpc_peering_graph(G)
