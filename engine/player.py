class Player():
  def __init__(self, player_id: int, name: str, team: str, position: str | list[str], recruited: bool = False):
    """
    player_id

    player_name

    team_name

    list of positions
    """
    self.id = player_id
    self.full_name = name
    self.team = team
    if type(position) is list:
      self.position = position
    else:
      self.position = [position]
    self.recruited = recruited # TODO check for valid status

    def toggle_status():
      self.recruited = not self.status