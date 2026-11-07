class Player():
  def __init__(self, player_id: int, name: str, team: str, position: str | list[str], status: str):
    """
    player_id

    player_name

    team_name

    list of positions
    """
    self.id = player_id
    self.name = name
    self.team = team
    if type(position) is list:
      self.position = position
    else:
      self.position = [position]
    self.status = status # TODO check for valid status