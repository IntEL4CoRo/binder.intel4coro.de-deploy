#!/usr/bin/env python
# coding: utf-8

# # Insert repo whitelist and ip whitelist to binder.yaml

# In[1]:


import yaml
import requests
import dns.resolver
import argparse

def fetch_json_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes
        json_data = response.json()
        return json_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching JSON data from URL: {e}")
        return None

def resolve_ips(domain):
  """
  Resolves the IP addresses of a given domain name.

  Args:
      domain: The domain name to resolve.

  Returns:
      A list of IP addresses for the given domain name.
  """
  try:
    # Use dns.resolver.query to get A records (IP addresses)
    result = dns.resolver.resolve(domain, 'A')
    return [str(ip.address) for ip in result]
  except dns.resolver.ResolverError:
    # Handle potential errors during resolution
    print(f"Error resolving IP addresses for domain: {domain}")
    return []


# In[6]:

def str_presenter(dumper, data):
    """configures yaml for dumping multiline strings
    Ref: https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data"""
    if data.count('\n') > 0:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description="My Script Description")
    # Define arguments with options, help messages, and type conversion
    parser.add_argument("-i", "--input", help="Input yaml file", type=str, default="binder.yaml")
    parser.add_argument("-o", "--output", help="Output yaml file", type=str, default="_binder.yaml")

    # Parse arguments
    args = parser.parse_args()
    
    # # load input yaml file
    print(f'Loading config file {args.input}')
    with open(args.input, 'r') as file:
        binder_yaml = yaml.safe_load(file)

    # Github repo whitelist
    if binder_yaml['config']['GitHubRepoProvider']['whitelist_enabled']:
        print('Applying Github Repo whitelist...')
        whitelist = binder_yaml['config']['GitHubRepoProvider']['whitelist']
        whitelist_reg = '^(?!(' + '|'.join(whitelist) + ')\/).*$'
        binder_yaml['config']['GitHubRepoProvider']['banned_specs'][0] = whitelist_reg
        binder_yaml['config']['GitHubRepoProvider'].pop('whitelist')
    else:
        binder_yaml['config'].pop('GitHubRepoProvider')

    whitelist_ip = []
    # Fetch IPs of domain name in fields 'domain_whitelist':
    domain_list = binder_yaml['jupyterhub']['singleuser']['networkPolicy']['domain_whitelist']
    binder_yaml['jupyterhub']['singleuser']['networkPolicy'].pop('domain_whitelist')
    for domain_name in domain_list:
        print(f'Fetching IPs of domain {domain_name} ...')
        whitelist_ip += [i + '/32' for i in resolve_ips(domain_name)]

    # Update Github server IPs
    print('Fetching IPs of GitHub Services ...')
    whitelist_ip += fetch_json_from_url('https://api.github.com/meta')['git']
    
    # Update pip.org IPs
    print('Fetching IPs of pip.org ...')
    whitelist_ip += fetch_json_from_url('https://api.fastly.com/public-ip-list')['addresses']

    # compose network policy
    print('Compose network policy rules ...')
    egress = binder_yaml['jupyterhub']['singleuser']['networkPolicy']['egress']
    ip_list = [{'ipBlock': {'cidr': f"{ip}"}} for ip in whitelist_ip]
    egress.append({'to': ip_list})

    # Save yaml config
    with open(args.output, 'w') as file:
        yaml.add_representer(str, str_presenter)
        file.write(yaml.dump(binder_yaml, indent=2))
        print(f'Config file {args.output} updated!')

if __name__ == "__main__":
    main()