using Agents

@agent struct Ghost(GridAgent{2})
    type::String = "Ghost"
end

function agent_step!(agent, model)
    randomwalk!(agent, model)
end

function initialize_model()
    space = GridSpace((10,10); periodic = false, metric = :manhattan)
    model = StandardABM(Ghost, space; agent_step!)
    return model
end

model = initialize_model()
add_agent!((5, 5), model; type="Ghost")