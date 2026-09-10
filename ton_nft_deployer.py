from tonsdk.utils import Address
from tonsdk.boc import Cell, DictBuilder
from tonsdk.contract.token.nft import NFTItem
import base64

def build_nft_content_cell(uri: str) -> Cell:
    """TEP-64 standartiga mos off-chain metadata cell (0x01 prefiksi va snake string)"""
    c = Cell()
    c.bits.write_uint8(1)  # Off-chain metadata prefix
    data = uri.encode('utf-8')
    avail = (1023 - c.bits.length) // 8
    chunk = data[:avail]
    c.bits.write_bytes(chunk)
    offset = len(chunk)
    cur = c
    while offset < len(data):
        next_cell = Cell()
        chunk = data[offset : offset + 127]
        next_cell.bits.write_bytes(chunk)
        offset += len(chunk)
        cur.refs.append(next_cell)
        cur = next_cell
    return c

def generate_nft_deploy_link(owner_wallet_address: str, ipfs_uri: str, amount_nano: int = 50000000) -> dict:
    try:
        owner_addr = Address(owner_wallet_address)
        content_cell = build_nft_content_cell(ipfs_uri)
        
        # Create NFT Item Contract
        nft = NFTItem(
            index=0,
            collection_address=None,
            owner_address=owner_addr,
            content=content_cell
        )
        
        state_init = nft.create_state_init()["state_init"]
        state_init_boc = state_init.to_boc(False)
        state_init_base64 = base64.urlsafe_b64encode(state_init_boc).decode('utf-8').replace('=', '')
        
        nft_address = nft.address.to_string(True, True, True)
        
        link = f"ton://transfer/{nft_address}?amount={amount_nano}&init={state_init_base64}"
        
        return {
            "nft_address": nft_address,
            "ton_link": link,
            "state_init": state_init_base64
        }
    except Exception as e:
        print(f"Error generating NFT deploy link: {e}")
        return {}

if __name__ == "__main__":
    link = generate_nft_deploy_link("0:1111111111111111111111111111111111111111111111111111111111111111", "ipfs://bafyreigx...")
    print(link)
