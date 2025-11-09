include("agents.jl")
using Genie, Genie.Renderer.Json, Genie.Requests, HTTP
using UUIDs

model = initialize_model()

route("/run") do
    step!(model, 1)
    #run!(model, 1)
    
    ghosts=[Tuple(a.pos) for a in allagents(model) if a isa Ghost]
    keys=[Tuple(a.pos) for a in allagents(model) if a isa Key && !a.collected]

    json(Dict(
        "ghost"=>ghosts,
        "keys"=>keys
    ))
end

Genie.config.run_as_server = true
Genie.config.cors_headers["Access-Control-Allow-Origin"] = "*"
Genie.config.cors_headers["Access-Control-Allow-Headers"] = "Content-Type"
Genie.config.cors_headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
Genie.config.cors_allowed_origins = ["*"]

up(8000, host="0.0.0.0")